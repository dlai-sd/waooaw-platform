// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-023 (Evidence First), C-007 (Append-Only), C-076 (Test Coverage)
using FluentAssertions;
using Grpc.Core;
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
/// CCT-EF-01 — Evidence First Enforcer constitutional compliance tests.
/// Constitutional basis: C-023 (Evidence First — audit record MUST be written before
/// RecordEvidence returns OK), C-007 (append-only — no UPDATE or DELETE may be issued).
/// Gate: CCT-EF-01 PASS is required before WC012-03 merge.
/// </summary>
public sealed class CCT_EF01_EvidenceFirstTests
{
    // ─── Helpers ────────────────────────────────────────────────────────────

    /// <summary>
    /// Minimal IDbContextFactory implementation that uses InMemoryDatabase.
    /// Using a shared options instance so the same DB is visible both to
    /// the service under test and to the assertion query.
    /// </summary>
    private sealed class FakeDbContextFactory : IDbContextFactory<ConstitutionalDbContext>
    {
        private readonly DbContextOptions<ConstitutionalDbContext> _options;

        public FakeDbContextFactory(DbContextOptions<ConstitutionalDbContext> options)
            => _options = options;

        public ConstitutionalDbContext CreateDbContext()
            => new ConstitutionalDbContext(_options);
    }

    /// <summary>
    /// Builds shared InMemory DbContextOptions keyed to a unique DB name so
    /// tests are fully isolated from each other.
    /// </summary>
    private static DbContextOptions<ConstitutionalDbContext> BuildInMemoryOptions()
        => new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

    /// <summary>
    /// Constructs a ConstitutionalEngineService with all real evaluators wired in
    /// (NullLogger suppresses noise) and the supplied factory.
    /// Constructor order (frozen WC012-03b): registry, logger, dbContextFactory.
    ///
    /// FIX (WC012-03c): EvaluatorRegistry constructor requires ILogger — pass
    /// NullLogger&lt;EvaluatorRegistry&gt;.Instance. CS7036 compile failure was
    /// caused by missing required 'logger' parameter on EvaluatorRegistry.
    /// Each evaluator constructor also requires ILogger&lt;T&gt;; use NullLogger&lt;T&gt;.Instance.
    /// </summary>
    private static ConstitutionalEngineService BuildService(
        IDbContextFactory<ConstitutionalDbContext> factory)
    {
        // Constitutional evaluators — real implementations, null loggers.
        // ⛔ CS7036 FIX: each evaluator constructor requires ILogger<T>; use NullLogger<T>.Instance.
        IClaimEvaluator[] evaluators =
        [
            new C041ToolAuthorizationEvaluator(NullLogger<C041ToolAuthorizationEvaluator>.Instance),
            new C043BudgetCeilingEvaluator(NullLogger<C043BudgetCeilingEvaluator>.Instance),
            new C048NonExploitationEvaluator(NullLogger<C048NonExploitationEvaluator>.Instance),
            new C049HonestLimitationEvaluator(NullLogger<C049HonestLimitationEvaluator>.Instance),
            new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance),
        ];

        // ⛔ CS7036 FIX (WC012-03c): EvaluatorRegistry requires ILogger<EvaluatorRegistry>.
        // Pass NullLogger<EvaluatorRegistry>.Instance — all-positional, no named args (CS1744).
        var registry = new EvaluatorRegistry(evaluators, NullLogger<EvaluatorRegistry>.Instance);
        var logger   = NullLogger<ConstitutionalEngineService>.Instance;

        // All-positional args — CS1744 forbidden (no named args after positional).
        return new ConstitutionalEngineService(registry, logger, factory);
    }

    /// <summary>
    /// Minimal valid RecordEvidenceRequest — PROPOSED state, required fields only.
    /// constitutional_basis must be non-empty (C-023 requirement; CE returns
    /// INVALID_ARGUMENT if it is empty).
    /// </summary>
    private static RecordEvidenceRequest BuildMinimalRequest(string contractId)
        => new RecordEvidenceRequest
        {
            ActionInstanceId     = Guid.NewGuid().ToString(),
            ContractId           = contractId,
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
            IsScopeBoundary      = false,
        };

    // ─── CCT-EF-01-A: Evidence written before response returned ─────────────

    /// <summary>
    /// C-023 (Evidence First): the service MUST persist the evidence record to the
    /// Constitutional Audit Ledger atomically BEFORE returning gRPC OK.
    /// After a successful RecordEvidence call the InMemory DB must contain exactly
    /// one EvidenceRecord row.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_WritesExactlyOneRecord_BeforeReturningResponse()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId   = Guid.NewGuid().ToString();
        var contractId = Guid.NewGuid().ToString();
        var grpcCtx    = FakeServerCallContext.Create(tenantId);
        var request    = BuildMinimalRequest(contractId);

        // Act
        var response = await svc.RecordEvidence(request, grpcCtx);

        // Assert — C-023: record must exist in ledger after the call returns.
        await using var assertCtx = new ConstitutionalDbContext(opts);
        var count = await assertCtx.EvidenceRecords.CountAsync();
        count.Should().Be(1,
            because: "C-023 requires the evidence record to be persisted " +
                     "before RecordEvidence returns success");

        // Sanity-check the response carries the assigned record ID.
        response.EvidenceRecordId.Should().NotBeNullOrEmpty(
            because: "C-023: response must carry the persisted record's UUID");
    }

    // ─── CCT-EF-01-B: Response evidence_record_id matches persisted row ─────

    /// <summary>
    /// C-023: the evidence_record_id returned in the response must correspond to
    /// the record actually written to the Constitutional Audit Ledger.
    /// This confirms the response is produced AFTER the write, not speculatively.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_ResponseId_MatchesPersistedRowId()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId   = Guid.NewGuid().ToString();
        var contractId = Guid.NewGuid().ToString();
        var grpcCtx    = FakeServerCallContext.Create(tenantId);
        var request    = BuildMinimalRequest(contractId);

        // Act
        var response = await svc.RecordEvidence(request, grpcCtx);

        // Assert — ID in response must match the row in the DB.
        await using var assertCtx = new ConstitutionalDbContext(opts);
        var record = await assertCtx.EvidenceRecords.SingleAsync();

        response.EvidenceRecordId.Should().Be(record.Id.ToString(),
            because: "the returned evidence_record_id must be the UUID of the " +
                     "actual persisted ledger row (C-023)");
    }

    // ─── CCT-EF-01-C: Tenant isolation — tenantId propagated from metadata ──

    /// <summary>
    /// C-005 / C-023: TenantId is sourced from gRPC metadata header 'x-tenant-id',
    /// never from the request body. The persisted record must carry the correct tenant.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_PersistsTenantId_FromGrpcMetadata()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId   = Guid.NewGuid().ToString();
        var contractId = Guid.NewGuid().ToString();
        var grpcCtx    = FakeServerCallContext.Create(tenantId);
        var request    = BuildMinimalRequest(contractId);

        // Act
        await svc.RecordEvidence(request, grpcCtx);

        // Assert — persisted TenantId must match the metadata value.
        await using var assertCtx = new ConstitutionalDbContext(opts);
        var record = await assertCtx.EvidenceRecords.SingleAsync();

        record.TenantId.ToString().Should().Be(tenantId,
            because: "tenant isolation (C-005) requires TenantId to come " +
                     "from x-tenant-id gRPC metadata, not the request body");
    }

    // ─── CCT-EF-01-D: Idempotency key is stored ─────────────────────────────

    /// <summary>
    /// C-023 / C-027: action_instance_id is stored as the idempotency key so that
    /// the append-only ledger can detect duplicate submissions. This guarantees
    /// exactly-once semantics on the ledger without needing UPDATE.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_PersistsActionInstanceId_AsIdempotencyKey()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId         = Guid.NewGuid().ToString();
        var contractId       = Guid.NewGuid().ToString();
        var actionInstanceId = Guid.NewGuid().ToString();
        var grpcCtx          = FakeServerCallContext.Create(tenantId);

        var request = new RecordEvidenceRequest
        {
            ActionInstanceId     = actionInstanceId,
            ContractId           = contractId,
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
            IsScopeBoundary      = false,
        };

        // Act
        await svc.RecordEvidence(request, grpcCtx);

        // Assert
        await using var assertCtx = new ConstitutionalDbContext(opts);
        var record = await assertCtx.EvidenceRecords.SingleAsync();

        record.IdempotencyKey.Should().Be(actionInstanceId,
            because: "action_instance_id must be stored as the idempotency key " +
                     "to enable duplicate detection without UPDATE (C-027)");
    }

    // ─── CCT-EF-01-E: Multiple sequential calls each write a new row ─────────

    /// <summary>
    /// C-007 / C-027 (Append-Only): every call to RecordEvidence must INSERT a new row.
    /// The ledger must never UPDATE an existing row.
    /// Calling RecordEvidence twice (e.g., PROPOSED then EXECUTED) must produce two rows.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_MultipleCallsOnSameContract_ProduceSeparateRows()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId         = Guid.NewGuid().ToString();
        var contractId       = Guid.NewGuid().ToString();
        var actionInstanceId = Guid.NewGuid().ToString();
        var grpcCtx          = FakeServerCallContext.Create(tenantId);

        var proposed = new RecordEvidenceRequest
        {
            ActionInstanceId     = actionInstanceId,
            ContractId           = contractId,
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
            IsScopeBoundary      = false,
        };

        var executed = new RecordEvidenceRequest
        {
            ActionInstanceId     = actionInstanceId,
            ContractId           = contractId,
            ProfessionalId       = proposed.ProfessionalId,
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Executed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
            IsScopeBoundary      = false,
        };

        // Act — two state transitions, both must produce a new INSERT.
        await svc.RecordEvidence(proposed, grpcCtx);
        await svc.RecordEvidence(executed, grpcCtx);

        // Assert — exactly two rows, never updated.
        await using var assertCtx = new ConstitutionalDbContext(opts);
        var count = await assertCtx.EvidenceRecords.CountAsync();

        count.Should().Be(2,
            because: "C-007/C-027 (append-only ledger): each state transition " +
                     "must produce a new INSERT row, never UPDATE an existing row");
    }

    // ─── CCT-EF-01-F: recorded_at timestamp is returned in response ──────────

    /// <summary>
    /// C-023: the RecordEvidenceResponse must carry a recorded_at timestamp that
    /// is set to the time of the DB write. This is the constitutional proof timestamp.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_Response_CarriesRecordedAtTimestamp()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId   = Guid.NewGuid().ToString();
        var contractId = Guid.NewGuid().ToString();
        var grpcCtx    = FakeServerCallContext.Create(tenantId);
        var request    = BuildMinimalRequest(contractId);

        var before = DateTimeOffset.UtcNow.AddSeconds(-1);

        // Act
        var response = await svc.RecordEvidence(request, grpcCtx);

        var after = DateTimeOffset.UtcNow.AddSeconds(1);

        // Assert — recorded_at must be set and within the test window.
        response.RecordedAt.Should().NotBeNull(
            because: "C-023: the response must carry a recorded_at timestamp " +
                     "proving when the evidence was written to the ledger");

        var recordedAt = response.RecordedAt.ToDateTimeOffset();
        recordedAt.Should().BeAfter(before,
            because: "recorded_at must be >= the time the call started");
        recordedAt.Should().BeBefore(after,
            because: "recorded_at must be <= the time the call returned");
    }

    // ─── CCT-EF-01-G: empty constitutional_basis is rejected ─────────────────

    /// <summary>
    /// C-023 / AD-008: RecordEvidence must return gRPC INVALID_ARGUMENT when
    /// constitutional_basis is empty. Every evidence record must name its
    /// constitutional authority.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_EmptyConstitutionalBasis_ThrowsInvalidArgument()
    {
        // Arrange
        var opts    = BuildInMemoryOptions();
        var factory = new FakeDbContextFactory(opts);
        var svc     = BuildService(factory);

        var tenantId   = Guid.NewGuid().ToString();
        var contractId = Guid.NewGuid().ToString();
        var grpcCtx    = FakeServerCallContext.Create(tenantId);

        var request = new RecordEvidenceRequest
        {
            ActionInstanceId     = Guid.NewGuid().ToString(),
            ContractId           = contractId,
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = string.Empty,  // intentionally empty — must be rejected
            IsScopeBoundary      = false,
        };

        // Act
        Func<Task> act = async () => await svc.RecordEvidence(request, grpcCtx);

        // Assert — CE must reject with RpcException (INVALID_ARGUMENT) per C-023 / AD-008.
        await act.Should().ThrowAsync<RpcException>(
            because: "AD-008 requires CE to return INVALID_ARGUMENT when " +
                     "constitutional_basis is empty — every record must name its authority");
    }
}