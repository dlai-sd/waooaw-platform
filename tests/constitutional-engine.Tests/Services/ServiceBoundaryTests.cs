// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-001, C-005, C-023, C-059, C-076, C-078, C-085
using FluentAssertions;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class ServiceBoundaryTests
{
    private sealed class Factory<TContext>(DbContextOptions<TContext> options)
        : IDbContextFactory<TContext>
        where TContext : DbContext
    {
        public TContext CreateDbContext() =>
            (TContext)Activator.CreateInstance(typeof(TContext), options)!;
    }

    private sealed class ThrowingFactory<TContext> : IDbContextFactory<TContext>
        where TContext : DbContext
    {
        public TContext CreateDbContext() =>
            throw new InvalidOperationException("database unavailable");
    }

    private sealed class ThrowingEvaluator : IClaimEvaluator
    {
        public string ClaimId => "TEST";

        public Task<EvaluationResult> EvaluateAsync(EvaluationContext context, CancellationToken cancellationToken) =>
            throw new InvalidOperationException("evaluation failed");
    }

    private static DbContextOptions<TContext> Options<TContext>()
        where TContext : DbContext =>
        new DbContextOptionsBuilder<TContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

    private static EvaluatorRegistry Registry(params IClaimEvaluator[]? evaluators) =>
        new(
            evaluators is { Length: > 0 }
                ? evaluators
                :
            [
                new C041ToolAuthorizationEvaluator(NullLogger<C041ToolAuthorizationEvaluator>.Instance),
                new C043BudgetCeilingEvaluator(NullLogger<C043BudgetCeilingEvaluator>.Instance),
                new C048NonExploitationEvaluator(NullLogger<C048NonExploitationEvaluator>.Instance),
                new C049HonestLimitationEvaluator(NullLogger<C049HonestLimitationEvaluator>.Instance),
                new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance),
            ],
            NullLogger<EvaluatorRegistry>.Instance);

    private static ConstitutionalEngineService Service(
        IDbContextFactory<ConstitutionalDbContext>? constitutionalFactory = null,
        IDbContextFactory<EmergencyStopDbContext>? emergencyFactory = null,
        IDbContextFactory<AuditSinkDbContext>? auditFactory = null,
        EvaluatorRegistry? registry = null) =>
        new(
            registry ?? Registry(),
            NullLogger<ConstitutionalEngineService>.Instance,
            constitutionalFactory ?? new Factory<ConstitutionalDbContext>(Options<ConstitutionalDbContext>()),
            emergencyFactory!,
            null!,
            auditFactory);

    private static RecordEvidenceRequest EvidenceRequest(string actionInstanceId) => new()
    {
        ActionInstanceId = actionInstanceId,
        ActionType = "MCP_TOOL_CALL",
        State = EvidenceState.Proposed,
        ConstitutionalBasis = "C-023",
        ProposedContent = "{\"tool\":\"read_file\"}",
    };

    [Theory]
    [InlineData(null, StatusCode.Unauthenticated)]
    [InlineData("", StatusCode.Unauthenticated)]
    [InlineData("not-a-uuid", StatusCode.Unauthenticated)]
    public async Task RecordEvidence_RejectsInvalidTenant(string? tenantId, StatusCode expected)
    {
        var act = () => Service().RecordEvidence(
            EvidenceRequest("action-1"),
            FakeServerCallContext.Create(tenantId));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(expected);
    }

    [Fact]
    public async Task RecordEvidence_RequiresActionInstanceId()
    {
        var request = EvidenceRequest(string.Empty);

        var act = () => Service().RecordEvidence(
            request,
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.InvalidArgument);
    }

    [Fact]
    public async Task RecordEvidence_DuplicateState_ReturnsExistingRecord()
    {
        var options = Options<ConstitutionalDbContext>();
        var service = Service(new Factory<ConstitutionalDbContext>(options));
        var context = FakeServerCallContext.Create(Guid.NewGuid().ToString());
        var request = EvidenceRequest("idempotent-action");

        var first = await service.RecordEvidence(request, context);
        var second = await service.RecordEvidence(request, context);

        second.EvidenceRecordId.Should().Be(first.EvidenceRecordId);
        await using var db = new ConstitutionalDbContext(options);
        (await db.EvidenceRecords.SingleAsync()).PayloadJson.Should().Be(request.ProposedContent);
    }

    [Fact]
    public async Task RecordEvidence_WhenDatabaseFails_ReturnsInternal()
    {
        var act = () => Service(new ThrowingFactory<ConstitutionalDbContext>()).RecordEvidence(
            EvidenceRequest("action-failure"),
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
        error.Which.Status.Detail.Should().Contain("database unavailable");
    }

    [Fact]
    public async Task ValidateAction_RequiresTenant()
    {
        var act = () => Service().ValidateAction(new ValidateActionRequest(), FakeServerCallContext.Create());

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public async Task ValidateAction_HonestLimitation_ReturnsEscalate()
    {
        var response = await Service().ValidateAction(
            new ValidateActionRequest
            {
                ContractId = "contract-escalate",
                ActionType = "MCP_TOOL_CALL",
                ActionParameters = "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\",\"uncertainty_acknowledged\":\"true\"}",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        response.Decision.Should().Be(ValidationDecision.Escalate);
        response.ConstitutionalBasis.Should().Be("C-049");
    }

    [Fact]
    public async Task ValidateAction_WhenEvaluatorFails_ReturnsInternal()
    {
        var service = Service(registry: Registry(new ThrowingEvaluator()));

        var act = () => service.ValidateAction(
            new ValidateActionRequest { ContractId = "contract-failure" },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
        error.Which.Status.Detail.Should().Contain("evaluation failed");
    }

    [Fact]
    public async Task EvaluatePolicy_WhenEvaluatorFails_ReturnsInternal()
    {
        var service = Service(registry: Registry(new ThrowingEvaluator()));

        var act = () => service.EvaluatePolicy(
            new EvaluatePolicyRequest
            {
                ContractId = "contract-failure",
                ActionType = "MCP_TOOL_CALL",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
        error.Which.Status.Detail.Should().Contain("evaluation failed");
    }

    [Theory]
    [InlineData(null, "00000000-0000-0000-0000-000000000001", "customer", StatusCode.Unauthenticated)]
    [InlineData("not-a-uuid", "00000000-0000-0000-0000-000000000001", "customer", StatusCode.Unauthenticated)]
    [InlineData("00000000-0000-0000-0000-000000000001", "not-a-uuid", "customer", StatusCode.InvalidArgument)]
    [InlineData("00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002", "", StatusCode.InvalidArgument)]
    public async Task TriggerEmergencyStop_RejectsInvalidInput(
        string? tenantId,
        string contractId,
        string stoppedBy,
        StatusCode expected)
    {
        var request = new EmergencyStopRequest { ContractId = contractId, StoppedBy = stoppedBy };

        var act = () => Service().TriggerEmergencyStop(request, FakeServerCallContext.Create(tenantId));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(expected);
    }

    [Fact]
    public async Task TriggerEmergencyStop_WithoutConfiguredDatabase_ReturnsInternal()
    {
        var act = () => Service().TriggerEmergencyStop(
            new EmergencyStopRequest
            {
                ContractId = Guid.NewGuid().ToString(),
                StoppedBy = "customer-1",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
    }

    [Fact]
    public async Task TriggerEmergencyStop_PersistsBeforeReturning()
    {
        var options = Options<EmergencyStopDbContext>();
        var tenantId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        var request = new EmergencyStopRequest
        {
            ContractId = contractId.ToString(),
            StoppedBy = "customer-1",
        };
        request.ActiveSessionIds.Add("session-1");

        var response = await Service(
            emergencyFactory: new Factory<EmergencyStopDbContext>(options)).TriggerEmergencyStop(
                request,
                FakeServerCallContext.Create(tenantId.ToString()));

        response.EmergencyStopRecordId.Should().StartWith("EMERGENCY_STOP:");
        response.AffectedSessions.Should().Equal("session-1");
        await using var db = new EmergencyStopDbContext(options);
        var record = await db.EmergencyStopEvents.SingleAsync();
        record.ContractId.Should().Be(contractId);
        record.InitiatedByUserId.Should().Be("customer-1");
        record.AffectedSessionIds.Should().Equal("session-1");
    }

    [Fact]
    public async Task TriggerEmergencyStop_WhenDatabaseFails_ReturnsInternal()
    {
        var act = () => Service(
            emergencyFactory: new ThrowingFactory<EmergencyStopDbContext>()).TriggerEmergencyStop(
                new EmergencyStopRequest
                {
                    ContractId = Guid.NewGuid().ToString(),
                    StoppedBy = "customer-1",
                },
                FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
    }

    [Theory]
    [InlineData(null, StatusCode.Unauthenticated)]
    [InlineData("not-a-uuid", StatusCode.Unauthenticated)]
    public async Task QueryEvidenceRecords_RejectsInvalidTenant(string? tenantId, StatusCode expected)
    {
        var act = () => Service().QueryEvidenceRecords(
            new QueryEvidenceRecordsRequest(),
            FakeServerCallContext.Create(tenantId));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(expected);
    }

    [Fact]
    public async Task QueryEvidenceRecords_RejectsInvalidShape()
    {
        var request = new QueryEvidenceRecordsRequest { PageSize = 101 };
        request.EvidenceRecordIds.Add(Guid.NewGuid().ToString());

        var act = () => Service().QueryEvidenceRecords(
            request,
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.InvalidArgument);
    }

    [Fact]
    public async Task QueryEvidenceRecords_RequiresAuditSink()
    {
        var request = new QueryEvidenceRecordsRequest();
        request.EvidenceRecordIds.Add(Guid.NewGuid().ToString());

        var act = () => Service().QueryEvidenceRecords(
            request,
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Unavailable);
    }

    [Fact]
    public async Task QueryEvidenceRecords_RejectsMalformedEvidenceId()
    {
        var request = new QueryEvidenceRecordsRequest();
        request.EvidenceRecordIds.Add("not-a-uuid");

        var act = () => Service(auditFactory: new Factory<AuditSinkDbContext>(Options<AuditSinkDbContext>()))
            .QueryEvidenceRecords(request, FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.InvalidArgument);
    }

    [Fact]
    public async Task QueryEvidenceRecords_ReturnsVisibleOptionalFields()
    {
        var options = Options<AuditSinkDbContext>();
        var tenantId = Guid.NewGuid();
        var record = new AuditSinkEvidenceRecord
        {
            Id = Guid.NewGuid(),
            DecisionId = "DEC-VISIBLE",
            TenantId = tenantId,
            AgentId = "agent",
            AgentInstanceId = "relationship",
            ActionType = "MCP_TOOL_CALL",
            ToolName = "read_file",
            ArgsHash = new string('a', 64),
            ExecutionStatus = "AUTHORIZED",
            ConstitutionalBasis = ["C-041"],
            EvidenceHash = new string('b', 64),
            PayloadRefId = Guid.NewGuid(),
            ErasureStatus = "NONE",
        };
        await using (var db = new AuditSinkDbContext(options))
        {
            db.EvidenceRecords.Add(record);
            await db.SaveChangesAsync();
        }
        var request = new QueryEvidenceRecordsRequest();
        request.EvidenceRecordIds.Add(record.Id.ToString());

        var response = await Service(auditFactory: new Factory<AuditSinkDbContext>(options))
            .QueryEvidenceRecords(request, FakeServerCallContext.Create(tenantId.ToString()));

        response.Records.Should().ContainSingle();
        response.Records[0].ToolName.Should().Be("read_file");
        response.Records[0].ArgsHash.Should().Be(record.ArgsHash);
        response.Records[0].PayloadRefId.Should().Be(record.PayloadRefId.ToString());
    }

    [Theory]
    [InlineData("", "order-1")]
    [InlineData("not-a-uuid", "order-1")]
    [InlineData("00000000-0000-0000-0000-000000000001", "")]
    public async Task RecordErasure_RejectsInvalidRequest(string tenantId, string orderId)
    {
        var act = () => Service().RecordErasure(
            new RecordErasureRequest { TenantId = tenantId, ErasureOrderId = orderId },
            FakeServerCallContext.Create(tenantId));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.InvalidArgument);
    }

    [Fact]
    public async Task RecordErasure_WithoutAuditSink_ReturnsSuccessfulNoOp()
    {
        var response = await Service().RecordErasure(
            new RecordErasureRequest
            {
                TenantId = Guid.NewGuid().ToString(),
                ErasureOrderId = "order-1",
            },
            FakeServerCallContext.Create());

        response.Success.Should().BeTrue();
        response.RecordsUpdated.Should().Be(0);
    }

    [Fact]
    public async Task RecordErasure_WhenDatabaseFails_ReturnsInternal()
    {
        var act = () => Service(auditFactory: new ThrowingFactory<AuditSinkDbContext>()).RecordErasure(
            new RecordErasureRequest
            {
                TenantId = Guid.NewGuid().ToString(),
                ErasureOrderId = "order-1",
            },
            FakeServerCallContext.Create());

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
    }
}
