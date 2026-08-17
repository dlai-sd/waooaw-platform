// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-023, C-036, C-059, C-076
using System.Buffers.Binary;
using System.Net;
using System.Security.Claims;
using System.Text.Json;
using Google.Protobuf;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ConstitutionalGrpcCoverageTests
{
    [Fact]
    public async Task RelationshipGateway_AllowsAndRecordsCanonicalEvidence()
    {
        var evidenceId = Guid.NewGuid();
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse
            {
                Decision = ValidationDecision.Allow,
                ConstitutionalBasis = "C-023; C-059",
            },
            _ => new RecordEvidenceResponse { EvidenceRecordId = evidenceId.ToString("D") });
        var gateway = new RelationshipConstitutionalGateway(
            Configuration(server.Address), NullLogger<RelationshipConstitutionalGateway>.Instance);

        var result = await gateway.AuthorizeAndRecordAsync(
            Guid.NewGuid(), Guid.NewGuid(), "DMA", "TEST_ACTION", Guid.NewGuid(),
            new { value = "canonical" }, CancellationToken.None);

        Assert.Equal(evidenceId, result);
        Assert.Equal(1, server.ValidateCalls);
        Assert.Equal(1, server.RecordCalls);
    }

    [Theory]
    [InlineData(ValidationDecision.Deny, "denied", "denied")]
    [InlineData(ValidationDecision.Escalate, "", "Escalate")]
    public async Task RelationshipGateway_RejectsNonAllowDecision(
        ValidationDecision decision,
        string reason,
        string expected)
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse { Decision = decision, Reason = reason },
            _ => new RecordEvidenceResponse { EvidenceRecordId = Guid.NewGuid().ToString("D") });
        var gateway = new RelationshipConstitutionalGateway(
            Configuration(server.Address), NullLogger<RelationshipConstitutionalGateway>.Instance);

        var exception = await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            gateway.AuthorizeAndRecordAsync(
                Guid.NewGuid(), Guid.NewGuid(), "DMA", "TEST_ACTION", Guid.NewGuid(),
                new { }, CancellationToken.None));

        Assert.Contains(expected, exception.Message);
        Assert.Equal(0, server.RecordCalls);
    }

    [Fact]
    public async Task RelationshipGateway_RejectsInvalidEvidenceIdentifier()
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse { Decision = ValidationDecision.Allow },
            _ => new RecordEvidenceResponse { EvidenceRecordId = "invalid" });
        var gateway = new RelationshipConstitutionalGateway(
            Configuration(server.Address), NullLogger<RelationshipConstitutionalGateway>.Instance);

        await Assert.ThrowsAsync<InvalidOperationException>(() => gateway.AuthorizeAndRecordAsync(
            Guid.NewGuid(), Guid.NewGuid(), "DMA", "TEST_ACTION", Guid.NewGuid(),
            new { }, CancellationToken.None));
    }

    [Fact]
    public async Task SkillPublish_AllowsCreationThenRejectsDuplicateVersion()
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse { Decision = ValidationDecision.Allow },
            _ => new RecordEvidenceResponse());
        var options = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = new SkillsController(
            new DbFactory<SkillCatalogDbContext>(options),
            Configuration(server.Address),
            NullLogger<SkillsController>.Instance)
        {
            ControllerContext = FounderContext(),
        };
        var request = new PublishSkillRequest(
            "skill", "1", "Skill", JsonDocument.Parse("{\"schema\":1}").RootElement, ["CCT-1"]);

        var created = await controller.PublishSkillAsync(request, CancellationToken.None);
        var duplicate = await controller.PublishSkillAsync(request, CancellationToken.None);

        Assert.IsType<CreatedAtActionResult>(created);
        Assert.IsType<ConflictObjectResult>(duplicate);
    }

    [Theory]
    [InlineData(ValidationDecision.Deny)]
    [InlineData(ValidationDecision.Escalate)]
    public async Task SkillPublish_RejectsNonAllowDecision(ValidationDecision decision)
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse
            {
                Decision = decision,
                Reason = "outside authority",
                ConstitutionalBasis = "C-036",
            },
            _ => new RecordEvidenceResponse());
        var options = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = new SkillsController(
            new DbFactory<SkillCatalogDbContext>(options),
            Configuration(server.Address),
            NullLogger<SkillsController>.Instance)
        {
            ControllerContext = FounderContext(),
        };

        var result = Assert.IsType<ObjectResult>(await controller.PublishSkillAsync(
            new PublishSkillRequest(
                "skill", "1", "Skill", JsonDocument.Parse("{}").RootElement, ["CCT-1"]),
            CancellationToken.None));

        Assert.Equal(403, result.StatusCode);
    }

    [Theory]
    [InlineData(ValidationDecision.Allow, 201)]
    [InlineData(ValidationDecision.Deny, 403)]
    [InlineData(ValidationDecision.Unspecified, 503)]
    public async Task CustomerRegistration_MapsConstitutionalDecision(
        ValidationDecision decision,
        int expectedStatus)
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse { Decision = decision },
            _ => new RecordEvidenceResponse());
        var fixture = RelationshipFixture();
        var controller = CustomerController(fixture, server.Address);

        var result = await controller.RegisterCustomerAsync(
            new RegisterCustomerRequest("Customer", "customer@example.com", fixture.TenantId.ToString("D")),
            CancellationToken.None);

        var actualStatus = result switch
        {
            ForbidResult => StatusCodes.Status403Forbidden,
            ObjectResult objectResult => objectResult.StatusCode,
            _ => null,
        };
        Assert.Equal(expectedStatus, actualStatus);
    }

    [Theory]
    [InlineData(ValidationDecision.Allow, 200)]
    [InlineData(ValidationDecision.Deny, 403)]
    public async Task SkillAmendment_MapsConstitutionalDecision(
        ValidationDecision decision,
        int expectedStatus)
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse
            {
                Decision = decision,
                Reason = "policy",
                ConstitutionalBasis = "C-036",
            },
            _ => new RecordEvidenceResponse());
        var fixture = RelationshipFixture();
        var controller = CustomerController(fixture, server.Address);

        var result = await controller.AmendContractAsync(
            new AmendContractRequest("contract", "skill", "1", "REMOVE"),
            CancellationToken.None);

        Assert.Equal(expectedStatus, Assert.IsAssignableFrom<ObjectResult>(result).StatusCode);
    }

    [Theory]
    [InlineData(ValidationDecision.Allow, true)]
    [InlineData(ValidationDecision.Deny, false)]
    public async Task EmploymentService_MapsRegistrationAndHireDecisions(
        ValidationDecision decision,
        bool expectedSuccess)
    {
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse { Decision = decision, Reason = "policy" },
            _ => new RecordEvidenceResponse());
        var service = new EmploymentService(
            Configuration(server.Address), NullLogger<EmploymentService>.Instance);

        var registration = await service.RegisterCustomerAsync(
            new RegisterCustomerRequest("Name\nQuoted", "customer\\\"@example.com", Guid.NewGuid().ToString()),
            CancellationToken.None);
        var hire = await service.HireAgentAsync(
            new HireAgentRequest("contract", "DMA\t", "publish", "invalid", 100, "1\r"),
            CancellationToken.None);

        Assert.Equal(expectedSuccess, registration.Success);
        Assert.Equal(expectedSuccess, hire.Success);
        Assert.Equal(expectedSuccess, registration.CustomerId.HasValue);
        Assert.Equal(expectedSuccess, hire.AgentId.HasValue);
        Assert.Equal(expectedSuccess, hire.ProRataBillingStartDate.HasValue);
    }

    [Fact]
    public async Task CustomerDataErasure_WipesPayloadAndReturnsCeCertificate()
    {
        const string erasureOrderId = "DPDPA-ORDER-1";
        var tenantId = Guid.NewGuid();
        await using var server = await RawConstitutionalServer.StartAsync(
            _ => new ValidateActionResponse(),
            _ => new RecordEvidenceResponse(),
            request => new RecordErasureResponse
            {
                RecordsUpdated = request.TenantId == tenantId.ToString("D") ? 2 : 0,
            });
        var options = new DbContextOptionsBuilder<PayloadStoreDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        await using (var db = new PayloadStoreDbContext(options))
        {
            db.OperationalPayloads.AddRange(
                Payload(tenantId),
                Payload(tenantId),
                Payload(Guid.NewGuid()));
            await db.SaveChangesAsync();
        }
        var controller = new CustomerDataController(
            new DbFactory<PayloadStoreDbContext>(options),
            new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["ConstitutionalEngine:GrpcAddress"] = server.Address.ToString(),
            }).Build(),
            NullLogger<CustomerDataController>.Instance)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(
                        [new Claim(ClaimTypes.Role, "founder")], "Test")),
                },
            },
        };

        var result = Assert.IsType<OkObjectResult>(await controller.EraseCustomerDataAsync(
            tenantId, erasureOrderId, CancellationToken.None));

        var certificate = JsonSerializer.SerializeToElement(result.Value);
        Assert.Equal(2, certificate.GetProperty("records_wiped").GetInt32());
        Assert.Equal(2, certificate.GetProperty("ce_records_marked").GetInt32());
        await using var check = new PayloadStoreDbContext(options);
        Assert.All(
            await check.OperationalPayloads.Where(value => value.TenantId == tenantId).ToListAsync(),
            value =>
            {
                Assert.Null(value.PayloadJson);
                Assert.NotNull(value.ErasedAt);
            });
        Assert.Single(await check.OperationalPayloads.Where(value => value.ErasedAt == null).ToListAsync());
    }

    private static IConfiguration Configuration(Uri address) => new ConfigurationBuilder()
        .AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["ConstitutionalEngine:GrpcUrl"] = address.ToString(),
        })
        .Build();

    private static ControllerContext FounderContext() => new()
    {
        HttpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity([new Claim("role", "founder")], "Test")),
        },
    };

    private static RelationshipTestFixture RelationshipFixture()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        return new(
            new EmploymentRelationshipService(
                factory,
                new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance),
            Guid.NewGuid(),
            Guid.NewGuid());
    }

    private static CustomersController CustomerController(RelationshipTestFixture fixture, Uri address)
    {
        var skillOptions = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = new CustomersController(
            Configuration(address),
            new DbFactory<SkillCatalogDbContext>(skillOptions),
            fixture.Service,
            NullLogger<CustomersController>.Instance);
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim("participant_id", fixture.ParticipantId.ToString("D"))], "Test")),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = fixture.TenantId.ToString("D");
        controller.ControllerContext = new ControllerContext { HttpContext = context };
        return controller;
    }

    private static OperationalPayload Payload(Guid tenantId) => new()
    {
        Id = Guid.NewGuid(),
        PayloadRefId = Guid.NewGuid(),
        TenantId = tenantId,
        AgentInstanceId = "agent",
        ActionType = "TEST",
        PayloadJson = "{\"personal\":true}",
        PayloadBlobRef = "payload-ref",
    };

    private sealed record RelationshipTestFixture(
        EmploymentRelationshipService Service,
        Guid TenantId,
        Guid ParticipantId);

    private sealed class DbFactory<TContext>(DbContextOptions<TContext> options)
        : IDbContextFactory<TContext>
        where TContext : DbContext
    {
        public TContext CreateDbContext() =>
            (TContext)Activator.CreateInstance(typeof(TContext), options)!;
    }
}

internal sealed class RawConstitutionalServer : IAsyncDisposable
{
    private const string ServicePath = "/constitutional.v1.ConstitutionalService/";
    private readonly WebApplication _application;

    private RawConstitutionalServer(WebApplication application, Uri address)
    {
        _application = application;
        Address = address;
    }

    public Uri Address { get; }
    public int ValidateCalls { get; private set; }
    public int RecordCalls { get; private set; }

    public static async Task<RawConstitutionalServer> StartAsync(
        Func<ValidateActionRequest, ValidateActionResponse> validate,
        Func<RecordEvidenceRequest, RecordEvidenceResponse> record,
        Func<RecordErasureRequest, RecordErasureResponse>? erase = null)
    {
        var listener = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        var builder = WebApplication.CreateSlimBuilder();
        builder.WebHost.ConfigureKestrel(options => options.Listen(
            IPAddress.Loopback,
            port,
            listen => listen.Protocols = HttpProtocols.Http2));
        var application = builder.Build();
        var server = new RawConstitutionalServer(application, new Uri($"http://127.0.0.1:{port}"));
        application.MapPost(ServicePath + "ValidateAction", context => server.ReplyAsync(
            context,
            ValidateActionRequest.Parser,
            request =>
            {
                server.ValidateCalls++;
                return validate(request);
            }));
        application.MapPost(ServicePath + "RecordEvidence", context => server.ReplyAsync(
            context,
            RecordEvidenceRequest.Parser,
            request =>
            {
                server.RecordCalls++;
                return record(request);
            }));
        application.MapPost(ServicePath + "RecordErasure", context => server.ReplyAsync(
            context,
            RecordErasureRequest.Parser,
            request => erase?.Invoke(request) ?? new RecordErasureResponse()));
        await application.StartAsync();
        return server;
    }

    private async Task ReplyAsync<TRequest, TResponse>(
        HttpContext context,
        MessageParser<TRequest> parser,
        Func<TRequest, TResponse> responseFactory)
        where TRequest : IMessage<TRequest>
        where TResponse : IMessage<TResponse>
    {
        var header = new byte[5];
        await context.Request.Body.ReadExactlyAsync(header);
        var payload = new byte[BinaryPrimitives.ReadInt32BigEndian(header.AsSpan(1))];
        await context.Request.Body.ReadExactlyAsync(payload);
        var response = responseFactory(parser.ParseFrom(payload)).ToByteArray();
        var frame = new byte[response.Length + 5];
        BinaryPrimitives.WriteInt32BigEndian(frame.AsSpan(1, 4), response.Length);
        response.CopyTo(frame.AsSpan(5));
        context.Response.ContentType = "application/grpc";
        context.Response.DeclareTrailer("grpc-status");
        await context.Response.Body.WriteAsync(frame);
        context.Response.AppendTrailer("grpc-status", "0");
    }

    public async ValueTask DisposeAsync() => await _application.DisposeAsync();
}
