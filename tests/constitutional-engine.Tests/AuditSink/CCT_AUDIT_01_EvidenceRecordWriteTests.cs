// Implements: work-contracts/WC-037-trust-layer-s1-audit-trail-sink.md §WC037-06
// constitutional_basis: C-059 (Traceability), C-076 (≥90% coverage), ADR-044
using FluentAssertions;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.AuditSink;

/// <summary>
/// CCT-AUDIT-01 — every ValidateAction path writes exactly one audit_sink evidence record.
/// WORM assertion: no UpdateRange / DeleteRange issued (verified by record count stability).
/// ADR-044 §5, C-059.
/// </summary>
public sealed class CCT_AUDIT_01_EvidenceRecordWriteTests
{
    // ─── Factories ──────────────────────────────────────────────────────────

    private static DbContextOptions<ConstitutionalDbContext> BuildConstOptions() =>
        new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

    private static DbContextOptions<AuditSinkDbContext> BuildAuditOptions() =>
        new DbContextOptionsBuilder<AuditSinkDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

    private sealed class FakeConstFactory : IDbContextFactory<ConstitutionalDbContext>
    {
        private readonly DbContextOptions<ConstitutionalDbContext> _opts;
        public FakeConstFactory(DbContextOptions<ConstitutionalDbContext> opts) => _opts = opts;
        public ConstitutionalDbContext CreateDbContext() => new(_opts);
    }

    private sealed class FakeAuditFactory : IDbContextFactory<AuditSinkDbContext>
    {
        private readonly DbContextOptions<AuditSinkDbContext> _opts;
        public FakeAuditFactory(DbContextOptions<AuditSinkDbContext> opts) => _opts = opts;
        public AuditSinkDbContext CreateDbContext() => new(_opts);
    }

    private static ConstitutionalEngineService BuildService(
        IDbContextFactory<ConstitutionalDbContext> constFactory,
        IDbContextFactory<AuditSinkDbContext> auditFactory)
    {
        IClaimEvaluator[] evaluators =
        [
            new C041ToolAuthorizationEvaluator(NullLogger<C041ToolAuthorizationEvaluator>.Instance),
            new C043BudgetCeilingEvaluator(NullLogger<C043BudgetCeilingEvaluator>.Instance),
            new C048NonExploitationEvaluator(NullLogger<C048NonExploitationEvaluator>.Instance),
            new C049HonestLimitationEvaluator(NullLogger<C049HonestLimitationEvaluator>.Instance),
            new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance),
        ];
        var registry = new EvaluatorRegistry(evaluators, NullLogger<EvaluatorRegistry>.Instance);
        return new ConstitutionalEngineService(
            registry,
            NullLogger<ConstitutionalEngineService>.Instance,
            constFactory,
            null!,
            null!,
            auditFactory);
    }

    private static ValidateActionRequest BuildAllowRequest(string contractId) =>
        new ValidateActionRequest
        {
            ContractId           = contractId,
            ActionType           = "MCP_TOOL_CALL",
            ActionParameters     = "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\"}",
            DecisionSpaceVersion = 1,
        };

    private static ValidateActionRequest BuildDenyRequest(string contractId) =>
        new ValidateActionRequest
        {
            ContractId           = contractId,
            ActionType           = "MCP_TOOL_CALL",
            ActionParameters     = "{\"tool_name\":\"unauthorized_tool\"}",
            DecisionSpaceVersion = 1,
        };

    // ─── CCT-AUDIT-01-A: ALLOW path writes one audit_sink row ───────────────

    [Fact]
    public async Task ValidateAction_AllowPath_WritesOneAuditSinkRow()
    {
        var auditOpts   = BuildAuditOptions();
        var constOpts   = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc         = BuildService(new FakeConstFactory(constOpts), auditFactory);
        var tenantId    = Guid.NewGuid().ToString();
        var ctx         = FakeServerCallContext.Create(tenantId);

        var response = await svc.ValidateAction(BuildAllowRequest("contract-allow"), ctx);

        response.Decision.Should().Be(ValidationDecision.Allow);

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var count = await assertDb.EvidenceRecords.CountAsync();
        count.Should().Be(1, because: "ADR-044: every ValidateAction writes exactly one audit_sink row");

        var row = await assertDb.EvidenceRecords.FirstAsync();
        row.ExecutionStatus.Should().Be("AUTHORIZED");
        row.TenantId.Should().Be(Guid.Parse(tenantId));
        row.ErasureStatus.Should().Be("NONE", because: "new records start with NONE erasure status");
        row.EvidenceHash.Should().NotBeNullOrEmpty(because: "C-059: hash is mandatory for traceability");
    }

    // ─── CCT-AUDIT-01-B: DENY path writes one row with DENIED status ────────

    [Fact]
    public async Task ValidateAction_DenyPath_WritesAuditRowWithDeniedStatus()
    {
        var auditOpts    = BuildAuditOptions();
        var constOpts    = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc          = BuildService(new FakeConstFactory(constOpts), auditFactory);
        var tenantId     = Guid.NewGuid().ToString();
        var ctx          = FakeServerCallContext.Create(tenantId);

        // C041 evaluator denies MCP_TOOL_CALL with "unauthorized_tool"
        var response = await svc.ValidateAction(BuildDenyRequest("contract-deny"), ctx);

        response.Decision.Should().Be(ValidationDecision.Deny);

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var row = await assertDb.EvidenceRecords.FirstAsync();
        row.ExecutionStatus.Should().Be("DENIED");
    }

    // ─── CCT-AUDIT-01-C: three calls produce three independent rows ─────────

    [Fact]
    public async Task ValidateAction_ThreeCalls_ThreeIndependentRows()
    {
        var auditOpts    = BuildAuditOptions();
        var constOpts    = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc          = BuildService(new FakeConstFactory(constOpts), auditFactory);
        var tenantId     = Guid.NewGuid().ToString();
        var ctx          = FakeServerCallContext.Create(tenantId);

        await svc.ValidateAction(BuildAllowRequest("c1"), ctx);
        await svc.ValidateAction(BuildAllowRequest("c2"), ctx);
        await svc.ValidateAction(BuildAllowRequest("c3"), ctx);

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var count = await assertDb.EvidenceRecords.CountAsync();
        count.Should().Be(3, because: "ADR-044: one row per ValidateAction call");
    }

    // ─── CCT-AUDIT-01-D: WORM — existing rows stay NONE after new insert ────

    [Fact]
    public async Task AuditSinkRows_ErasureStatusStaysNone_UnlessExplicitlyUpdated()
    {
        var auditOpts    = BuildAuditOptions();
        var constOpts    = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc          = BuildService(new FakeConstFactory(constOpts), auditFactory);
        var tenantId     = Guid.NewGuid().ToString();
        var ctx          = FakeServerCallContext.Create(tenantId);

        await svc.ValidateAction(BuildAllowRequest("contract-worm"), ctx);
        await svc.ValidateAction(BuildAllowRequest("contract-worm2"), ctx);

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var rows = await assertDb.EvidenceRecords.ToListAsync();
        rows.Should().AllSatisfy(r => r.ErasureStatus.Should().Be("NONE"),
            because: "C-059: WORM — no write path sets erasure_status except RecordErasure RPC");
    }

    // ─── CCT-AUDIT-01-E: RecordErasure stamps PAYLOAD_PURGED ────────────────

    [Fact]
    public async Task RecordErasure_StampsPayloadPurged_OnTenantRows()
    {
        var auditOpts    = BuildAuditOptions();
        var constOpts    = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc          = BuildService(new FakeConstFactory(constOpts), auditFactory);
        var tenantId     = Guid.NewGuid();
        var ctx          = FakeServerCallContext.Create(tenantId.ToString());
        var erasureCtx   = FakeServerCallContext.Create(tenantId.ToString());

        // Write two audit rows.
        await svc.ValidateAction(BuildAllowRequest("c-erase"), ctx);
        await svc.ValidateAction(BuildAllowRequest("c-erase2"), ctx);

        var erasureReq = new RecordErasureRequest
        {
            TenantId       = tenantId.ToString(),
            ErasureOrderId = "DPDPA-ORDER-001"
        };
        var erasureResp = await svc.RecordErasure(erasureReq, erasureCtx);

        erasureResp.Success.Should().BeTrue();
        erasureResp.RecordsUpdated.Should().Be(2,
            because: "both rows for this tenant must be stamped");

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var rows = await assertDb.EvidenceRecords.ToListAsync();
        rows.Should().AllSatisfy(r =>
        {
            r.ErasureStatus.Should().Be("PAYLOAD_PURGED");
            r.ErasureTimestamp.Should().NotBeNull();
        }, because: "ADR-044 §4: RecordErasure stamps all tenant rows");
    }

    // ─── CCT-AUDIT-01-F: RecordErasure — wrong tenant is not affected ───────

    [Fact]
    public async Task RecordErasure_DoesNotAffectOtherTenantRows()
    {
        var auditOpts    = BuildAuditOptions();
        var constOpts    = BuildConstOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var svc          = BuildService(new FakeConstFactory(constOpts), auditFactory);

        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        var ctxA    = FakeServerCallContext.Create(tenantA.ToString());
        var ctxB    = FakeServerCallContext.Create(tenantB.ToString());

        await svc.ValidateAction(BuildAllowRequest("contract-A"), ctxA);
        await svc.ValidateAction(BuildAllowRequest("contract-B"), ctxB);

        var erasureResp = await svc.RecordErasure(
            new RecordErasureRequest { TenantId = tenantA.ToString(), ErasureOrderId = "ORD-002" },
            ctxA);

        erasureResp.RecordsUpdated.Should().Be(1);

        await using var assertDb = new AuditSinkDbContext(auditOpts);
        var bRow = await assertDb.EvidenceRecords
            .FirstAsync(r => r.TenantId == tenantB);
        bRow.ErasureStatus.Should().Be("NONE",
            because: "tenant B's data must not be affected by tenant A's erasure order");
    }

    [Fact]
    public async Task QueryEvidenceRecords_OmitsForeignTenantAndErasedPayloadReference()
    {
        var auditOpts = BuildAuditOptions();
        var auditFactory = new FakeAuditFactory(auditOpts);
        var tenantId = Guid.NewGuid();
        var ownId = Guid.NewGuid();
        var foreignId = Guid.NewGuid();
        await using (var db = new AuditSinkDbContext(auditOpts))
        {
            db.EvidenceRecords.AddRange(
                new AuditSinkEvidenceRecord
                {
                    Id = ownId, TenantId = tenantId, DecisionId = "DEC-OWN", AgentId = "agent",
                    AgentInstanceId = "relationship", ActionType = "EMERGENCY_STOP",
                    ExecutionStatus = "AUTHORIZED", ConstitutionalBasis = ["C-001"],
                    EvidenceHash = new string('a', 64), PayloadRefId = Guid.NewGuid(),
                    ErasureStatus = "PAYLOAD_PURGED", ErasureTimestamp = DateTimeOffset.UtcNow,
                },
                new AuditSinkEvidenceRecord
                {
                    Id = foreignId, TenantId = Guid.NewGuid(), DecisionId = "DEC-FOREIGN", AgentId = "agent",
                    AgentInstanceId = "relationship", ActionType = "PAYMENT",
                    ExecutionStatus = "AUTHORIZED", ConstitutionalBasis = ["C-023"],
                    EvidenceHash = new string('b', 64), PayloadRefId = Guid.NewGuid(),
                });
            await db.SaveChangesAsync();
        }
        var service = BuildService(new FakeConstFactory(BuildConstOptions()), auditFactory);
        var request = new QueryEvidenceRecordsRequest { PageSize = 100 };
        request.EvidenceRecordIds.AddRange([ownId.ToString(), foreignId.ToString()]);

        var response = await service.QueryEvidenceRecords(
            request, FakeServerCallContext.Create(tenantId.ToString()));

        response.Records.Should().ContainSingle();
        response.Records[0].EvidenceRecordId.Should().Be(ownId.ToString());
        response.Records[0].HasPayloadRefId.Should().BeFalse();
        response.Records[0].ErasureTimestamp.Should().NotBeNull();
    }
}
