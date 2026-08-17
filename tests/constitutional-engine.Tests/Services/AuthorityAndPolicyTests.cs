// Implements: architecture/reference/components/constitutional-engine.md sections 3 and 5
// constitutional_basis: C-003, C-005, C-023, C-048, C-049, C-076
using System.Text.Json;
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

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class AuthorityAndPolicyTests
{
    private sealed class InMemoryFactory(DbContextOptions<ConstitutionalDbContext> options)
        : IDbContextFactory<ConstitutionalDbContext>
    {
        public ConstitutionalDbContext CreateDbContext() => new(options);
    }

    private sealed class ThrowingFactory : IDbContextFactory<ConstitutionalDbContext>
    {
        public ConstitutionalDbContext CreateDbContext() =>
            throw new InvalidOperationException("ledger unavailable");
    }

    private static DbContextOptions<ConstitutionalDbContext> BuildOptions() =>
        new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

    private static ConstitutionalEngineService BuildService(
        IDbContextFactory<ConstitutionalDbContext> factory)
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
            factory);
    }

    [Fact]
    public async Task GrantAuthorityLicense_PersistsTraceableEvidence()
    {
        var options = BuildOptions();
        var service = BuildService(new InMemoryFactory(options));
        var tenantId = Guid.NewGuid();
        var request = new GrantAuthorityRequest
        {
            ContractId = "contract-42",
            NewAuthorityLevel = 3,
            GrantedBy = "customer-7",
            ConstitutionalBasis = "C-003; C-023",
        };
        request.EvidenceIds.Add("evidence-1");
        request.EvidenceIds.Add("evidence-2");

        var response = await service.GrantAuthorityLicense(
            request,
            FakeServerCallContext.Create(tenantId.ToString()));

        Guid.TryParse(response.LicenseId, out var licenseId).Should().BeTrue();
        response.RecordedAt.Should().NotBeNull();
        await using var db = new ConstitutionalDbContext(options);
        var record = await db.EvidenceRecords.SingleAsync();
        record.Id.Should().Be(licenseId);
        record.TenantId.Should().Be(tenantId);
        record.EvidenceType.Should().Be("AUTHORITY_GRANT");
        record.IdempotencyKey.Should().StartWith("GRANT:contract-42:");
        record.Summary.Should().Contain("level 3").And.Contain("customer-7");
        using var payload = JsonDocument.Parse(record.PayloadJson!);
        payload.RootElement.GetProperty("evidenceIds").GetArrayLength().Should().Be(2);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("not-a-uuid")]
    public async Task GrantAuthorityLicense_RejectsInvalidTenant(string? tenantId)
    {
        var service = BuildService(new InMemoryFactory(BuildOptions()));
        var request = new GrantAuthorityRequest { ContractId = "contract", GrantedBy = "customer" };
        request.EvidenceIds.Add("evidence-1");

        var act = () => service.GrantAuthorityLicense(request, FakeServerCallContext.Create(tenantId));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public async Task GrantAuthorityLicense_RequiresEvidence()
    {
        var service = BuildService(new InMemoryFactory(BuildOptions()));
        var request = new GrantAuthorityRequest { ContractId = "contract", GrantedBy = "customer" };

        var act = () => service.GrantAuthorityLicense(
            request,
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.InvalidArgument);
    }

    [Fact]
    public async Task GrantAuthorityLicense_WhenLedgerFails_ReturnsInternal()
    {
        var service = BuildService(new ThrowingFactory());
        var request = new GrantAuthorityRequest { ContractId = "contract", GrantedBy = "customer" };
        request.EvidenceIds.Add("evidence-1");

        var act = () => service.GrantAuthorityLicense(
            request,
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
        error.Which.Status.Detail.Should().Contain("ledger unavailable");
    }

    [Fact]
    public async Task RevokeAuthorityLicense_PersistsRestrictionEvidence()
    {
        var options = BuildOptions();
        var service = BuildService(new InMemoryFactory(options));
        var tenantId = Guid.NewGuid();
        var request = new RevokeAuthorityRequest
        {
            ContractId = "contract-42",
            NewAuthorityLevel = 1,
            RevokedBy = "customer-7",
            Reason = "risk threshold changed",
            ConstitutionalBasis = "C-003; C-023",
        };

        var response = await service.RevokeAuthorityLicense(
            request,
            FakeServerCallContext.Create(tenantId.ToString()));

        Guid.TryParse(response.LicenseId, out var licenseId).Should().BeTrue();
        await using var db = new ConstitutionalDbContext(options);
        var record = await db.EvidenceRecords.SingleAsync();
        record.Id.Should().Be(licenseId);
        record.TenantId.Should().Be(tenantId);
        record.EvidenceType.Should().Be("AUTHORITY_REVOKE");
        record.IdempotencyKey.Should().StartWith("REVOKE:contract-42:");
        record.Summary.Should().Contain("level 1").And.Contain("customer-7");
        record.PayloadJson.Should().Contain("risk threshold changed");
    }

    [Fact]
    public async Task RevokeAuthorityLicense_RejectsInvalidTenant()
    {
        var service = BuildService(new InMemoryFactory(BuildOptions()));

        var act = () => service.RevokeAuthorityLicense(
            new RevokeAuthorityRequest { ContractId = "contract" },
            FakeServerCallContext.Create("not-a-uuid"));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public async Task RevokeAuthorityLicense_WhenLedgerFails_ReturnsInternal()
    {
        var service = BuildService(new ThrowingFactory());

        var act = () => service.RevokeAuthorityLicense(
            new RevokeAuthorityRequest { ContractId = "contract" },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Internal);
    }

    [Fact]
    public async Task EvaluatePolicy_PermitsCompliantAction()
    {
        var response = await BuildService(new InMemoryFactory(BuildOptions())).EvaluatePolicy(
            new EvaluatePolicyRequest
            {
                ContractId = "contract-42",
                ActionType = "MCP_TOOL_CALL",
                ActionContext = "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\"}",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        response.Decision.Should().Be(PolicyDecision.Permit);
        response.ConstitutionalBasis.Should().Contain("C-003");
    }

    [Fact]
    public async Task EvaluatePolicy_DeniesExploitativeAction()
    {
        var response = await BuildService(new InMemoryFactory(BuildOptions())).EvaluatePolicy(
            new EvaluatePolicyRequest
            {
                ContractId = "contract-42",
                ActionType = "MCP_TOOL_CALL",
                ActionContext = "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\",\"content_type\":\"HIGH_PRESSURE_SALES\"}",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        response.Decision.Should().Be(PolicyDecision.Deny);
        response.ConstitutionalBasis.Should().Be("C-048");
    }

    [Fact]
    public async Task EvaluatePolicy_EscalatesHonestLimitation()
    {
        var response = await BuildService(new InMemoryFactory(BuildOptions())).EvaluatePolicy(
            new EvaluatePolicyRequest
            {
                ContractId = "contract-42",
                ActionType = "MCP_TOOL_CALL",
                ActionContext = "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\",\"uncertainty_acknowledged\":\"true\"}",
            },
            FakeServerCallContext.Create(Guid.NewGuid().ToString()));

        response.Decision.Should().Be(PolicyDecision.Escalate);
        response.ConstitutionalBasis.Should().Be("C-049");
    }

    [Fact]
    public async Task EvaluatePolicy_RequiresTenant()
    {
        var act = () => BuildService(new InMemoryFactory(BuildOptions())).EvaluatePolicy(
            new EvaluatePolicyRequest { ContractId = "contract", ActionType = "GENERATE_REPORT" },
            FakeServerCallContext.Create());

        var error = await act.Should().ThrowAsync<RpcException>();
        error.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }
}
